/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // "/" is the standalone landing page in public/landing/index.html (plain HTML, no framework)
  async rewrites() {
    return { beforeFiles: [{ source: "/", destination: "/landing/index.html" }], afterFiles: [], fallback: [] };
  },
  // the landing page links to /dashboard/<page> and /about-data; map them to the routes that exist
  async redirects() {
    return [
      { source: "/dashboard/:page(assistant|explorer|data|insights|compare|report)", destination: "/:page", permanent: false },
      { source: "/about-data", destination: "/about", permanent: false },
    ];
  },
};
export default nextConfig;
