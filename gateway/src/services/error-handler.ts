import { Request, RequestHandler, Response, NextFunction } from 'express';

export interface NodeError extends Error {
  code: string;
  reason: string;
}

// custom error for http exceptions
export class HttpException extends Error {
  status: number;
  message: string;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.message = message;
  }
}

export class GatewayError extends Error {
  message: string;
  errorCode: number;
  httpErrorCode: number;
  constructor(httpErrorCode: number, errorCode: number, message: string) {
    super(message);
    this.httpErrorCode = httpErrorCode;
    this.errorCode = errorCode;
    this.message = message;
  }
}

// Capture errors from an async route, this must wrap any route that uses async.
// For example, `app.get('/', asyncHandler(async (req, res) -> {...}))`
export const asyncHandler =
  (fn: RequestHandler) => (req: Request, res: Response, next: NextFunction) => {
    return Promise.resolve(fn(req, res, next)).catch(next);
  };
