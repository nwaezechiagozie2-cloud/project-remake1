const INSTAGRAM_CLIENT_ID =
  process.env.NEXT_PUBLIC_INSTAGRAM_CLIENT_ID || "2049636778952216";
const INSTAGRAM_REDIRECT_URI =
  process.env.NEXT_PUBLIC_INSTAGRAM_REDIRECT_URI ||
  "https://one-tap-closer-dbd309d28017.herokuapp.com/auth/instagram/callback";

export const INSTAGRAM_OAUTH_URL =
  `https://www.instagram.com/oauth/authorize?force_reauth=true&client_id=${INSTAGRAM_CLIENT_ID}` +
  `&redirect_uri=${encodeURIComponent(INSTAGRAM_REDIRECT_URI)}` +
  `&response_type=code&scope=instagram_business_basic%2Cinstagram_business_manage_messages%2Cinstagram_business_manage_comments%2Cinstagram_business_content_publish%2Cinstagram_business_manage_insights`;
