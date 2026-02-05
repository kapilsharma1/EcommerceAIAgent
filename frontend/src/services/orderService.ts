import apiClient from './api'
import { OrderListResponse } from '../types/order'

export interface DelayedOrderResponse {
  order_id: string
  message: string
}

export const createDelayedOrder = async (): Promise<DelayedOrderResponse> => {
  const response = await apiClient.post<DelayedOrderResponse>('/orders/create-delayed')
  return response.data
}

export const getAllOrders = async (limit: number = 100, offset: number = 0): Promise<OrderListResponse> => {
  const response = await apiClient.get<OrderListResponse>('/orders', {
    params: { limit, offset },
  })
  return response.data
}
