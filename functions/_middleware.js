// Redirect the default *.pages.dev preview hostname to the canonical
// custom domain so traffic and Cloudflare Web Analytics stay on one
// property. _redirects can't match on hostname, hence this middleware.
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname.endsWith('.pages.dev')) {
    return Response.redirect(
      'https://trumpaccountbenefits.com' + url.pathname + url.search,
      301
    );
  }
  return context.next();
}
