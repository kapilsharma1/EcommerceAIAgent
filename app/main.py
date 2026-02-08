"""FastAPI main application."""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, timedelta
from app.config import settings
from app.models.database import init_db, AsyncSessionLocal
from app.models.domain import Order, OrderStatus
from app.actions.order_repository import OrderRepository
from app.observability.tracing import setup_observability
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific loggers to DEBUG for more detailed output
logging.getLogger("app").setLevel(logging.DEBUG)
logging.getLogger("app.api").setLevel(logging.DEBUG)
logging.getLogger("app.graph").setLevel(logging.DEBUG)
logging.getLogger("app.llm").setLevel(logging.DEBUG)
logging.getLogger("app.rag").setLevel(logging.DEBUG)
logging.getLogger("app.actions").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


async def seed_orders():
    """Seed database with mock orders if they don't exist."""
    logger.info("Seeding orders into database...")
    
    # Define mock orders (same as in mock_order_service.py)
    mock_orders = [
        Order(
            order_id="ORD-001",
            status=OrderStatus.PLACED,
            expected_delivery_date=date.today() + timedelta(days=5),
            amount=99.99,
            refundable=True,
            description="Wireless Bluetooth headphones with noise cancellation",
        ),
        Order(
            order_id="ORD-002",
            status=OrderStatus.SHIPPED,
            expected_delivery_date=date.today() + timedelta(days=2),
            amount=149.50,
            refundable=True,
            description="Smart fitness tracker with heart rate monitor",
        ),
        Order(
            order_id="ORD-003",
            status=OrderStatus.DELIVERED,
            expected_delivery_date=date.today() - timedelta(days=3),
            amount=79.99,
            refundable=True,
            description="Portable phone charger with fast charging support",
        ),
        Order(
            order_id="ORD-004",
            status=OrderStatus.CANCELLED,
            expected_delivery_date=date.today() + timedelta(days=7),
            amount=199.99,
            refundable=False,
            description="Premium leather wallet with RFID blocking",
        ),
        Order(
            order_id="ORD-005",
            status=OrderStatus.PLACED,
            expected_delivery_date=date.today() - timedelta(days=10),  # Delayed
            amount=299.99,
            refundable=True,
            description="4K Ultra HD streaming device with voice remote",
        ),
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            repository = OrderRepository(session)
            seeded_count = 0
            
            for order in mock_orders:
                exists = await repository.order_exists(order.order_id)
                if not exists:
                    await repository.create_order(order)
                    seeded_count += 1
                    logger.info(f"Seeded order: {order.order_id}")
                else:
                    logger.debug(f"Order {order.order_id} already exists, skipping")
            
            if seeded_count > 0:
                logger.info(f"Seeded {seeded_count} orders into database")
            else:
                logger.info("All orders already exist in database, no seeding needed")
        except Exception as e:
            logger.error(f"Error seeding orders: {str(e)}", exc_info=True)
            # Don't raise - allow app to start even if seeding fails


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("=" * 80)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 80)
    
    # Setup observability
    logger.info("Setting up observability...")
    setup_observability()
    logger.info("Observability configured")
    
    # Initialize database
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}", exc_info=True)
    
    # ============================================================================
    # TEMPORARY FIX: Clear conversations table on startup
    # ============================================================================
    # This ensures the conversations table is in sync with MemorySaver, which
    # starts empty on each app restart. This prevents orphaned conversations
    # (conversations in DB but no history in MemorySaver).
    #
    # MIGRATION TO POSTGRESSAVER - REMOVE THIS ENTIRE BLOCK:
    # ----------------------------------------------------------------------------
    # When migrating to PostgresSaver, you should:
    #
    # 1. REMOVE this entire block (lines below until "# End temporary fix")
    #
    # 2. UPDATE app/api/routes.py:
    #    - Replace `from langgraph.checkpoint.memory import MemorySaver` 
    #      with `from langgraph.checkpoint.postgres import PostgresSaver`
    #    - Replace `_shared_checkpointer = MemorySaver()` 
    #      with PostgresSaver initialization using your database connection
    #    - Update checkpointer initialization to use PostgresSaver.from_conn_string()
    #
    # 3. UPDATE app/graph/graph.py:
    #    - Remove `from langgraph.checkpoint.memory import MemorySaver`
    #    - Update build_agent_graph() to require checkpointer parameter (no default)
    #    - Remove the fallback to MemorySaver() if checkpointer is None
    #
    # 4. UPDATE requirements.txt:
    #    - Add: psycopg2-binary>=2.9.0 (or psycopg[binary] for psycopg3)
    #
    # 5. UPDATE app/main.py (this file):
    #    - Add PostgresSaver table initialization in startup:
    #      ```python
    #      from langgraph.checkpoint.postgres import PostgresSaver
    #      from app.config import settings
    #      
    #      # Initialize PostgresSaver tables
    #      db_url = settings.get_database_url
    #      sync_db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    #      checkpointer = PostgresSaver.from_conn_string(sync_db_url)
    #      await checkpointer.setup()  # Creates checkpoint tables
    #      ```
    #
    # 6. UPDATE app/api/routes.py delete_conversation endpoint:
    #    - Add logic to also delete checkpoints from PostgresSaver when deleting a conversation
    #    - PostgresSaver may have methods to delete checkpoints by thread_id
    #
    # 7. REMOVE app/conversations/repository.py:
    #    - Remove delete_all_conversations() method
    #
    # 8. REMOVE app/conversations/service.py:
    #    - Remove delete_all_conversations() method
    #
    # After migration, conversations and checkpoints will both persist in PostgreSQL,
    # so no need to clear on startup. Everything will survive app restarts.
    # ============================================================================
    try:
        logger.info("Clearing conversations table (temporary fix for MemorySaver sync)...")
        from app.conversations.service import ConversationService
        
        async with AsyncSessionLocal() as session:
            conversation_service = ConversationService(session)
            deleted_count = await conversation_service.delete_all_conversations()
            logger.info(f"Cleared {deleted_count} conversations from database")
            logger.warning("=" * 80)
            logger.warning("TEMPORARY FIX ACTIVE: Conversations cleared on startup")
            logger.warning("This ensures sync with MemorySaver (which is empty on restart)")
            logger.warning("REMOVE THIS BLOCK when migrating to PostgresSaver")
            logger.warning("=" * 80)
    except Exception as e:
        logger.warning(f"Could not clear conversations on startup: {e}", exc_info=True)
        # Don't fail startup if this fails
    # End temporary fix
    # ============================================================================
    
    # Seed orders
    try:
        await seed_orders()
    except Exception as e:
        logger.warning(f"Order seeding warning: {e}", exc_info=True)
    
    logger.info("Application startup complete")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("APPLICATION SHUTDOWN")
    logger.info("=" * 80)


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered customer support agent for e-commerce",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

