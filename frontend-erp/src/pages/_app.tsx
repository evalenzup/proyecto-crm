// src/pages/_app.tsx
import type { AppProps } from 'next/app';
import 'antd/dist/reset.css';       // importa el reset de Ant Design
//import '../styles/globals.css';     // si tienes estilos globales propios

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}

