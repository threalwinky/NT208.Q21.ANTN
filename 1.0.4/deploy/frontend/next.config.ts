import { readFileSync } from "fs";
import type { NextConfig } from "next";

function readDockerGateway() {
  try {
    const route = readFileSync("/proc/net/route", "utf8");
    const defaultRoute = route.split("\n").find((line) => line.includes("\t00000000\t"));
    const gatewayHex = defaultRoute?.split("\t")[2];
    if (!gatewayHex) return null;
    return [3, 2, 1, 0].map((index) => parseInt(gatewayHex.slice(index * 2, index * 2 + 2), 16)).join(".");
  } catch {
    return null;
  }
}

const dockerGateway = readDockerGateway();
const fallbackApiBase = dockerGateway ? `http://${dockerGateway}:8000/api/v1` : "http://localhost:8000/api/v1";
const apiProxyBase = (process.env.INTERNAL_API_BASE_URL ?? fallbackApiBase).replace(/\/$/, "");

const allowedDevOrigins = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "mowndark.threalwinky.id.vn")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  output: process.env.NODE_ENV === "production" ? "standalone" : undefined,
  allowedDevOrigins,
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
