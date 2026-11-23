import path from "node:path";
import { loadEnvConfig } from "@next/env";

// Load the repository-root .env so the API secret stays server-side.
loadEnvConfig(path.resolve(process.cwd(), ".."));

const nextConfig = { output: "standalone" };
export default nextConfig;
