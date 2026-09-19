import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // @cadence/schema is a workspace package linked via file: in package.json,
  // shipping raw .ts source (no build step) -- transpilePackages tells
  // Next's compiler to process it like first-party code instead of
  // skipping it the way node_modules is skipped by default.
  transpilePackages: ["@cadence/schema"],
};

export default nextConfig;
