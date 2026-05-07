// src/app.d.ts
import type { User } from '$lib/types/user'; // wherever your User type lives

declare global {
    namespace App {
        interface Locals {
            user: User | null;
        }
    }
}

export {};