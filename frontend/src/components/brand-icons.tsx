export function GoogleIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z" />
    </svg>
  );
}

export function InstagramIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <defs>
        <radialGradient id="instagram-gradient-a" cx="30%" cy="107%" r="150%">
          <stop offset="0" stopColor="#FEDA75" />
          <stop offset="0.25" stopColor="#FA7E1E" />
          <stop offset="0.5" stopColor="#D62976" />
          <stop offset="0.75" stopColor="#962FBF" />
          <stop offset="1" stopColor="#4F5BD5" />
        </radialGradient>
      </defs>
      <path fill="url(#instagram-gradient-a)" d="M7.2 2h9.6A5.2 5.2 0 0 1 22 7.2v9.6a5.2 5.2 0 0 1-5.2 5.2H7.2A5.2 5.2 0 0 1 2 16.8V7.2A5.2 5.2 0 0 1 7.2 2zm0 1.8a3.4 3.4 0 0 0-3.4 3.4v9.6a3.4 3.4 0 0 0 3.4 3.4h9.6a3.4 3.4 0 0 0 3.4-3.4V7.2a3.4 3.4 0 0 0-3.4-3.4H7.2z" />
      <path fill="url(#instagram-gradient-a)" d="M12 7.05A4.95 4.95 0 1 1 12 16.95 4.95 4.95 0 0 1 12 7.05zm0 1.8A3.15 3.15 0 1 0 12 15.15 3.15 3.15 0 0 0 12 8.85z" />
      <circle cx="17.2" cy="6.8" r="1.2" fill="url(#instagram-gradient-a)" />
    </svg>
  );
}

export function WhatsAppIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#25D366"
        d="M12.04 2A9.88 9.88 0 0 0 2.1 11.83c0 1.74.46 3.44 1.32 4.93L2 22l5.39-1.38a10.05 10.05 0 0 0 4.65 1.14A9.88 9.88 0 0 0 22 11.93 9.9 9.9 0 0 0 12.04 2zm0 1.78a8.1 8.1 0 0 1 8.16 8.15 8.1 8.1 0 0 1-8.16 8.05 8.2 8.2 0 0 1-4.18-1.14l-.3-.18-3.2.82.85-3.08-.2-.32a8.06 8.06 0 0 1-1.14-4.25 8.1 8.1 0 0 1 8.17-8.05zm-3.5 3.93c-.17 0-.44.06-.67.32-.23.25-.88.86-.88 2.1 0 1.24.9 2.44 1.03 2.6.13.17 1.75 2.8 4.33 3.8 2.14.84 2.58.67 3.04.63.46-.04 1.49-.61 1.7-1.2.21-.59.21-1.09.15-1.2-.06-.1-.23-.17-.49-.3-.25-.13-1.49-.73-1.72-.82-.23-.08-.4-.13-.56.13-.17.25-.65.82-.8.98-.15.17-.29.19-.54.06-.26-.13-1.08-.4-2.05-1.27-.76-.68-1.27-1.51-1.42-1.77-.15-.25-.02-.39.11-.52.12-.11.26-.3.39-.44.13-.15.17-.25.25-.42.09-.17.04-.32-.02-.44-.06-.13-.56-1.35-.77-1.85-.2-.49-.41-.42-.56-.43h-.52z"
      />
    </svg>
  );
}

export function TelegramIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#229ED9"
        d="M21.8 4.2c.3-1.2-.8-2.2-1.9-1.7L2.8 9.1c-1.2.5-1.2 2.2.1 2.6l4.4 1.4 1.7 5.5c.4 1.2 1.9 1.5 2.7.5l2.5-3.1 4.8 3.5c1 .7 2.3.2 2.6-1l3.2-14.3zM8.1 12.2l9.7-6c.4-.2.8.3.5.6l-8 7.2-.3 3.1-1.1-3.6-.8-1.3z"
      />
    </svg>
  );
}
