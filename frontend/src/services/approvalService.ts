import apiClient from './api'
import type { ApprovalRequest, ApprovalResponse } from '@/types/approval'

export const submitApproval = async (
  approvalId: string,
  status: 'APPROVED' | 'REJECTED'
): Promise<ApprovalResponse> => {
  const request: ApprovalRequest = { status }

  const response = await apiClient.post<ApprovalResponse>(
    `/approvals/${approvalId}`,
    request
  )
  return response.data
}
