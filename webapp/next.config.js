/** @type {import('next').NextConfig} */
// `next dev` and `next build` must NOT share one output folder: this project
// builds a static export, and a dev server writing into .next leaves chunks the
// production build (and the next dev run) cannot resolve -> "Cannot find module
// './161.js'". Give dev its own directory so the two never collide.
const isDev = process.env.NODE_ENV === 'development';

const nextConfig = {
  distDir: isDev ? '.next-dev' : '.next',
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
};
module.exports = nextConfig;
