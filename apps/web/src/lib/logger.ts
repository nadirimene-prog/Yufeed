const isDev = process.env.NODE_ENV === "development";

export const logger = {
  debug(...args: unknown[]) {
    if (isDev) console.debug(...args);
  },
  log(...args: unknown[]) {
    if (isDev) console.log(...args);
  },
  warn(...args: unknown[]) {
    if (isDev) console.warn(...args);
  },
  error(...args: unknown[]) {
    if (isDev) console.error(...args);
    const err = args.find((a) => a instanceof Error);
    if (err) {
      import("@/lib/error-reporting").then((m) => m.captureException(err));
    }
  },
};
