import { StatusCodes } from 'http-status-codes';
import { HttpException } from './error-handler';

export const invalidAmountError: string =
  'If amount is included it must be a string of a non-negative integer.';

export const invalidTokenError: string = 'The token param should be a string.';

export const invalidTxHashError: string = 'The txHash param must be a string.';

export const invalidTokenSymbolsError: string =
  'The tokenSymbols param should be an array of strings.';

export const isNaturalNumberString = (str: string): boolean => {
  return /^[0-9]+$/.test(str);
};

export const isIntegerString = (str: string): boolean => {
  return /^[+-]?[0-9]+$/.test(str);
};

export const isFloatString = (str: string): boolean => {
  if (isIntegerString(str)) {
    return true;
  }
  const decimalSplit = str.split('.');
  if (decimalSplit.length === 2) {
    return (
      isIntegerString(decimalSplit[0]) && isNaturalNumberString(decimalSplit[1])
    );
  }
  return false;
};

export const isFractionString = (str: string): boolean => {
  const fractionSplit = str.split('/');
  if (fractionSplit.length == 2) {
    return (
      isIntegerString(fractionSplit[0]) && isIntegerString(fractionSplit[1])
    );
  }
  return false;
};

// throw an error because the request parameter is malformed, collect all the
// errors related to the request to give the most information possible
export const throwIfErrorsExist = (
  errors: Array<string>,
  statusCode: number = StatusCodes.NOT_FOUND,
  req: any,
  headerMessage?: (req: any) => string
): void => {
  if (errors.length > 0) {
    let message = headerMessage ? `${headerMessage(req)}\n` : '';
    message += errors.join('\n');

    throw new HttpException(statusCode, message);
  }
};

export const missingParameter = (key: string): string => {
  return `The request is missing the key: ${key}`;
};

export type Validator = (target: any, index?: number) => Array<string>;

export type RequestValidator = (req: any) => void;

export const mkBranchingValidator = (
  branchingKey: string,
  branchingCondition: (req: any, key: string) => boolean,
  validator1: Validator,
  validator2: Validator
): Validator => {
  return (req: any) => {
    let errors: Array<string> = [];
    if (req[branchingKey]) {
      if (branchingCondition(req, branchingKey)) {
        errors = errors.concat(validator1(req));
      } else {
        errors = errors.concat(validator2(req));
      }
    } else {
      errors.push(missingParameter(branchingKey));
    }
    return errors;
  };
};

export const mkValidator = (
  key: string,
  errorMsg: string | ((target: any, index?: number) => string),
  condition: (target: any) => boolean,
  optional: boolean = false,
  useRequest: boolean = false
): Validator => {
  return (target: any, index?: number) => {
    const errors: Array<string> = [];

    let passed: boolean;
    if (useRequest) passed = condition(target);
    else if (!target[key] && !optional) {
      errors.push(missingParameter(key));

      return errors;
    } else passed = condition(target[key]);

    let error: string;
    if (!passed && !optional) {
      if (typeof errorMsg === 'string') error = errorMsg;
      else if (useRequest) error = errorMsg(target, index);
      else error = errorMsg(target[key], index);

      errors.push(error);
    }

    return errors;
  };
};

export const mkBatchValidator = (
  validators: Validator[],
  headerItemMessage?: (item: any, index?: number) => string
) => {
  return (items: any[]) => {
    const errors: string[] = [];

    for (const [index, item] of items.entries()) {
      const itemErrors: string[] = [];

      for (const validator of validators) {
        itemErrors.push(...validator(item, index));
      }

      if (itemErrors && itemErrors.length > 0) {
        if (headerItemMessage) errors.push(headerItemMessage(item, index));

        errors.push(...itemErrors);
      }
    }

    return errors;
  };
};

export const mkRequestValidator = (
  validators: Array<Validator>,
  statusCode?: number,
  headerMessage?: (req: any) => string
): RequestValidator => {
  return (req: any) => {
    let errors: Array<string> = [];
    validators.forEach(
      (validator: Validator) => (errors = errors.concat(validator(req)))
    );
    throwIfErrorsExist(errors, statusCode, req, headerMessage);
  };
};

// confirm that tokenSymbols is an array of strings
export const validateTokenSymbols: Validator = (req: any) => {
  const errors: Array<string> = [];
  if (req.tokenSymbols) {
    if (Array.isArray(req.tokenSymbols)) {
      req.tokenSymbols.forEach((symbol: any) => {
        if (typeof symbol !== 'string') {
          errors.push(invalidTokenSymbolsError);
        }
      });
    } else {
      errors.push(invalidTokenSymbolsError);
    }
  } else {
    errors.push(missingParameter('tokenSymbols'));
  }
  return errors;
};

export const isBase58 = (value: string): boolean =>
  /^[A-HJ-NP-Za-km-z1-9]*$/.test(value);

// confirm that token is a string
export const validateToken: Validator = mkValidator(
  'token',
  invalidTokenError,
  (val) => typeof val === 'string'
);

// if amount exists, confirm that it is a string of a natural number
export const validateAmount: Validator = mkValidator(
  'amount',
  invalidAmountError,
  (val) =>
    val === undefined ||
    (typeof val === 'string' && isNaturalNumberString(val)),
  true
);

export const validateTxHash: Validator = mkValidator(
  'txHash',
  invalidTxHashError,
  (val) => typeof val === 'string'
);
