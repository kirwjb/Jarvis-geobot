export {};

declare global {
  interface Window {
    Telegram: any;
  }
}

declare module "*.module.css" {
  const classes: { [key: string]: string };
  export default classes;
}