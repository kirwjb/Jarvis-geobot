import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App.tsx';
import './index.css';
import { init } from '@telegram-apps/sdk';


if (window.Telegram?.WebApp?.initData) {
  try {
    init();
    console.log("Telegram SDK initialized.");
  } catch (error) {
    console.error("SDK init error:", error);
  }
} else {
  console.warn("Running in Web Mode (No Telegram SDK)");
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);