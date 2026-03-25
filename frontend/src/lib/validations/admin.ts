import { z } from "zod";

export const createUserSchema = z.object({
  username: z
    .string()
    .min(1, "Username is required")
    .max(63, "Username is too long")
    .regex(/^[a-zA-Z0-9_.-]+$/, "Username contains invalid characters"),
  password: z.string().min(1, "Password is required").max(256, "Password is too long"),
  roles: z.array(z.string()).optional(),
});

export const changePasswordSchema = z.object({
  password: z.string().min(1, "Password is required").max(256, "Password is too long"),
});

export const createRoleSchema = z.object({
  name: z
    .string()
    .min(1, "Role name is required")
    .max(63, "Role name is too long")
    .regex(/^[a-zA-Z0-9_.-]+$/, "Role name contains invalid characters"),
  privileges: z.array(z.string()).min(1, "At least one privilege is required"),
  whitelist: z.string().optional(),
  readQuota: z.string().optional(),
  writeQuota: z.string().optional(),
});

export type CreateUserFormValues = z.infer<typeof createUserSchema>;
export type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;
export type CreateRoleFormValues = z.infer<typeof createRoleSchema>;
