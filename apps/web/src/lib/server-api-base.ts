import { resolveServerApiBaseUrl } from "@/lib/api-base";

export const SERVER_API_BASE_URL = resolveServerApiBaseUrl(process.env);
