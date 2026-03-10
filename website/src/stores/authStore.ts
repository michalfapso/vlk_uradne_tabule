import { atom } from 'nanostores';

export interface User {
  name?: string;
  email?: string;
  picture?: string;
}

export const $isAuthenticated = atom<boolean>(false);
export const $user = atom<User | null>(null);

export function setAuth(isAuthenticated: boolean, user: User | null = null) {
  $isAuthenticated.set(isAuthenticated);
  $user.set(user);
}

