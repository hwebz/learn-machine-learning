import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Deep Research AI Chatbot | Multi-Provider Reasoning",
  description: "Next.js front-end application with real-time multi-provider AI reasoning, thinking effort controls, and live SSE status tracking.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  function cleanBis() {
                    var els = document.querySelectorAll('[bis_skin_checked]');
                    for (var i = 0; i < els.length; i++) {
                      els[i].removeAttribute('bis_skin_checked');
                    }
                  }
                  cleanBis();
                  if (typeof MutationObserver !== 'undefined') {
                    var observer = new MutationObserver(function(mutations) {
                      for (var i = 0; i < mutations.length; i++) {
                        var m = mutations[i];
                        if (m.type === 'attributes' && m.attributeName === 'bis_skin_checked' && m.target) {
                          m.target.removeAttribute('bis_skin_checked');
                        }
                        if (m.type === 'childList') {
                          for (var j = 0; j < m.addedNodes.length; j++) {
                            var node = m.addedNodes[j];
                            if (node.nodeType === 1) {
                              if (node.hasAttribute && node.hasAttribute('bis_skin_checked')) {
                                node.removeAttribute('bis_skin_checked');
                              }
                              var sub = node.querySelectorAll ? node.querySelectorAll('[bis_skin_checked]') : [];
                              for (var k = 0; k < sub.length; k++) {
                                sub[k].removeAttribute('bis_skin_checked');
                              }
                            }
                          }
                        }
                      }
                    });
                    observer.observe(document.documentElement, {
                      attributes: true,
                      subtree: true,
                      childList: true,
                      attributeFilter: ['bis_skin_checked']
                    });
                    window.addEventListener('DOMContentLoaded', cleanBis);
                  }
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable}`} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}

