/**
 * Standardized API Error Handling
 *
 * Provides consistent error handling across all API calls with:
 * - Type-safe error objects
 * - User-friendly error messages
 * - Structured error logging
 * - Toast notifications (optional)
 */

export interface ApiError {
    message: string;
    statusCode?: number;
    details?: string;
    timestamp: string;
}

export interface ErrorHandlerOptions {
    /**
     * Custom error message to show to the user.
     * If not provided, will use a default message based on error type.
     */
    customMessage?: string;

    /**
     * Whether to show a toast notification.
     * Default: false (caller should handle UI display)
     */
    showToast?: boolean;

    /**
     * Whether to log the error to console.
     * Default: true in development, false in production
     */
    logError?: boolean;

    /**
     * Context information for error logging
     */
    context?: string;
}

/**
 * Parse error response from API
 */
function parseApiError(error: unknown): ApiError {
    const timestamp = new Date().toISOString();

    // Axios error with response
    if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as {
            message?: string;
            response?: {
                data?: {
                    detail?: string;
                    message?: string;
                    details?: string;
                };
                status?: number;
            };
        };
        return {
            message: axiosError.response?.data?.detail || axiosError.response?.data?.message || axiosError.message || 'An error occurred',
            statusCode: axiosError.response?.status,
            details: axiosError.response?.data?.details,
            timestamp,
        };
    }

    // Fetch error
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
        return {
            message: 'Unable to connect to server. Please check your internet connection.',
            statusCode: 0,
            timestamp,
        };
    }

    // Standard Error object
    if (error instanceof Error) {
        return {
            message: error.message,
            timestamp,
        };
    }

    // Unknown error type
    return {
        message: 'An unexpected error occurred',
        timestamp,
    };
}

/**
 * Get user-friendly error message based on status code
 */
function getUserFriendlyMessage(statusCode?: number, defaultMessage?: string): string {
    if (defaultMessage) return defaultMessage;

    switch (statusCode) {
        case 400:
            return 'Invalid request. Please check your input and try again.';
        case 401:
            return 'Authentication required. Please log in and try again.';
        case 403:
            return 'You do not have permission to perform this action.';
        case 404:
            return 'The requested resource was not found.';
        case 409:
            return 'This action conflicts with existing data.';
        case 422:
            return 'Validation failed. Please check your input.';
        case 429:
            return 'Too many requests. Please try again later.';
        case 500:
            return 'Server error. Please try again later.';
        case 503:
            return 'Service temporarily unavailable. Please try again later.';
        default:
            return 'An error occurred. Please try again.';
    }
}

/**
 * Handle API errors with standardized logging and user feedback
 *
 * @param error The error object from try/catch
 * @param options Configuration options
 * @returns Parsed ApiError object
 *
 * @example
 * ```typescript
 * try {
 *   const data = await fetchData();
 * } catch (error) {
 *   const apiError = handleApiError(error, {
 *     context: 'fetchData',
 *     customMessage: 'Failed to load data'
 *   });
 *   setError(apiError.message);
 * }
 * ```
 */
export function handleApiError(
    error: unknown,
    options: ErrorHandlerOptions = {}
): ApiError {
    const {
        customMessage,
        logError = process.env.NODE_ENV === 'development',
        context,
    } = options;

    // Parse the error
    const apiError = parseApiError(error);

    // Get user-friendly message
    const userMessage = getUserFriendlyMessage(apiError.statusCode, customMessage);
    apiError.message = userMessage;

    // Log error if enabled
    if (logError) {
        console.error(
            `[API Error${context ? ` - ${context}` : ''}]:`,
            {
                message: apiError.message,
                statusCode: apiError.statusCode,
                details: apiError.details,
                timestamp: apiError.timestamp,
                originalError: error,
            }
        );
    }

    // TODO: Send to error monitoring service (Sentry, LogRocket, etc.)
    // if (process.env.NODE_ENV === 'production') {
    //     Sentry.captureException(error, {
    //         contexts: {
    //             api: {
    //                 statusCode: apiError.statusCode,
    //                 message: apiError.message,
    //                 context,
    //             },
    //         },
    //     });
    // }

    return apiError;
}

/**
 * Type guard to check if error is an API error
 */
export function isApiError(error: unknown): error is ApiError {
    return (
        typeof error === 'object' &&
        error !== null &&
        'message' in error &&
        'timestamp' in error
    );
}

/**
 * Retry failed API calls with exponential backoff
 *
 * @param fn The async function to retry
 * @param options Retry configuration
 * @returns Promise that resolves with the function result or rejects with the final error
 *
 * @example
 * ```typescript
 * const data = await retryApiCall(
 *   () => fetch('/api/data').then(r => r.json()),
 *   { maxRetries: 3, delayMs: 1000 }
 * );
 * ```
 */
export async function retryApiCall<T>(
    fn: () => Promise<T>,
    options: {
        maxRetries?: number;
        delayMs?: number;
        onRetry?: (attempt: number, error: unknown) => void;
    } = {}
): Promise<T> {
    const { maxRetries = 3, delayMs = 1000, onRetry } = options;

    let lastError: unknown;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;

            // Don't retry on client errors (4xx) except 429 (rate limit)
            const apiError = parseApiError(error);
            if (
                apiError.statusCode &&
                apiError.statusCode >= 400 &&
                apiError.statusCode < 500 &&
                apiError.statusCode !== 429
            ) {
                throw error;
            }

            // Last attempt, throw error
            if (attempt === maxRetries) {
                throw error;
            }

            // Call onRetry callback
            if (onRetry) {
                onRetry(attempt + 1, error);
            }

            // Exponential backoff
            const delay = delayMs * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }

    throw lastError;
}
