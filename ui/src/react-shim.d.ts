declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

declare module "react" {
  export const useEffect: any;
  export const useMemo: any;
  export const useState: any;
  export const useRef: any;
  export type ReactNode = any;
}

declare module "react-dom/client" {
  export const createRoot: any;
}

declare module "react/jsx-runtime" {
  export const Fragment: any;
  export const jsx: any;
  export const jsxs: any;
}

declare module "mermaid" {
  const mermaid: any;
  export default mermaid;
}
