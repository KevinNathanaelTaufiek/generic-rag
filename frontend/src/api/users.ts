import api from './client'

export async function fetchUsers(): Promise<string[]> {
  const { data } = await api.get<{ users: string[] }>('/users')
  return data.users
}
