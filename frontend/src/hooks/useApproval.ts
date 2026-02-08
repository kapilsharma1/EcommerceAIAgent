import { useMutation, useQueryClient } from '@tanstack/react-query'
import { submitApproval } from '@/services/approvalService'
import type { ApprovalResponse } from '@/types/approval'

export const useApproval = () => {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: ({ approvalId, status }: { approvalId: string; status: 'APPROVED' | 'REJECTED' }) =>
      submitApproval(approvalId, status),
    onSuccess: (data: ApprovalResponse) => {
      // Invalidate any related queries if needed
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
    },
  })

  const handleApproval = (approvalId: string, status: 'APPROVED' | 'REJECTED') => {
    mutation.mutate({ approvalId, status })
  }

  return {
    submitApproval: handleApproval,
    isLoading: mutation.isPending,
    error: mutation.error,
    response: mutation.data,
  }
}
