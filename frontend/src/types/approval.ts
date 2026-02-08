export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export type ActionType = 'CANCEL_ORDER' | 'REFUND_ORDER' | 'NONE'

export interface Approval {
  approval_id: string
  order_id: string
  action: ActionType
  status: ApprovalStatus
  created_at: string
}

export interface ApprovalRequest {
  status: 'APPROVED' | 'REJECTED'
}

export interface ApprovalResponse {
  status: string
  message: string
}

export interface PendingApproval {
  approvalId: string
  orderId: string
  action: ActionType
  message: string
}
