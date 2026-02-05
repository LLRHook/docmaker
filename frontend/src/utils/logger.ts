/**
 * Simple logger utility for the frontend.
 * Logs to console with timestamps and log levels.
 */

type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

// Set minimum log level (can be changed for production)
const MIN_LEVEL: LogLevel = "debug";

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[MIN_LEVEL];
}

function formatTimestamp(): string {
  return new Date().toISOString().slice(11, 23);
}

function formatMessage(level: LogLevel, module: string, message: string, ...args: unknown[]): string {
  const timestamp = formatTimestamp();
  const prefix = `[${timestamp}] [${level.toUpperCase()}] [${module}]`;

  if (args.length > 0) {
    return `${prefix} ${message} ${JSON.stringify(args)}`;
  }
  return `${prefix} ${message}`;
}

export function createLogger(module: string) {
  return {
    debug(message: string, ...args: unknown[]) {
      if (shouldLog("debug")) {
        console.debug(formatMessage("debug", module, message, ...args));
      }
    },
    info(message: string, ...args: unknown[]) {
      if (shouldLog("info")) {
        console.info(formatMessage("info", module, message, ...args));
      }
    },
    warn(message: string, ...args: unknown[]) {
      if (shouldLog("warn")) {
        console.warn(formatMessage("warn", module, message, ...args));
      }
    },
    error(message: string, ...args: unknown[]) {
      if (shouldLog("error")) {
        console.error(formatMessage("error", module, message, ...args));
      }
    },
  };
}

// Default logger for general use
export const logger = createLogger("app");
