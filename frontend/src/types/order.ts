export type OrderStatus = 'PLACED' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED' | 'REFUNDED'

export interface Order {
  order_id: string
  status: OrderStatus
  expected_delivery_date: string
  amount: number
  refundable: boolean
}
