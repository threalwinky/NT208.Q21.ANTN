import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Studify",
  description: "Nền tảng đồng hành dành cho sinh viên UIT",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      data-theme="light"
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
