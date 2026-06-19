import "./globals.css";

export const metadata = {
  title: "Therepy",
  description: "Private therapy chat with Ollama"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
