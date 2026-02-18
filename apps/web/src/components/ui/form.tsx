"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { AlertCircle, Eye, EyeOff } from "lucide-react";

/**
 * Horizon Form System
 * Accessible, consistent form components with validation support
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Form Field Context
   ───────────────────────────────────────────────────────────────────────────── */

interface FormFieldContextValue {
  id: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
}

const FormFieldContext = React.createContext<FormFieldContextValue | null>(
  null,
);

function useFormField() {
  const context = React.useContext(FormFieldContext);
  if (!context) {
    throw new Error("Form components must be used within a FormField");
  }
  return context;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Form Field Component
   ───────────────────────────────────────────────────────────────────────────── */

interface FormFieldProps {
  children: React.ReactNode;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

function FormField({
  children,
  error,
  required,
  disabled,
  className,
}: FormFieldProps) {
  const id = React.useId();

  return (
    <FormFieldContext.Provider value={{ id, error, required, disabled }}>
      <div className={cn("space-y-1.5", className)}>{children}</div>
    </FormFieldContext.Provider>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Form Label Component
   ───────────────────────────────────────────────────────────────────────────── */

interface FormLabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  children: React.ReactNode;
  optional?: boolean;
}

const FormLabel = React.forwardRef<HTMLLabelElement, FormLabelProps>(
  ({ children, className, optional, ...props }, ref) => {
    const { id, required, error } = useFormField();

    return (
      <label
        ref={ref}
        htmlFor={id}
        className={cn(
          "flex items-center gap-1.5 text-sm font-medium",
          error ? "text-critical-400" : "text-foreground",
          className,
        )}
        {...props}
      >
        {children}
        {required && (
          <span className="text-critical-400" aria-hidden="true">
            *
          </span>
        )}
        {optional && (
          <span className="text-xs font-normal text-foreground-tertiary">
            (optional)
          </span>
        )}
      </label>
    );
  },
);
FormLabel.displayName = "FormLabel";

/* ─────────────────────────────────────────────────────────────────────────────
   Form Description Component
   ───────────────────────────────────────────────────────────────────────────── */

interface FormDescriptionProps
  extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

const FormDescription = React.forwardRef<
  HTMLParagraphElement,
  FormDescriptionProps
>(({ children, className, ...props }, ref) => {
  const { id } = useFormField();

  return (
    <p
      ref={ref}
      id={`${id}-description`}
      className={cn("text-xs text-foreground-secondary", className)}
      {...props}
    >
      {children}
    </p>
  );
});
FormDescription.displayName = "FormDescription";

/* ─────────────────────────────────────────────────────────────────────────────
   Form Error Component
   ───────────────────────────────────────────────────────────────────────────── */

interface FormErrorProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children?: React.ReactNode;
}

const FormError = React.forwardRef<HTMLParagraphElement, FormErrorProps>(
  ({ children, className, ...props }, ref) => {
    const { id, error } = useFormField();

    if (!error && !children) return null;

    return (
      <p
        ref={ref}
        id={`${id}-error`}
        className={cn(
          "flex items-center gap-1.5 text-xs text-critical-400",
          className,
        )}
        role="alert"
        {...props}
      >
        <AlertCircle className="h-3.5 w-3.5 shrink-0" />
        {children || error}
      </p>
    );
  },
);
FormError.displayName = "FormError";

/* ─────────────────────────────────────────────────────────────────────────────
   Input Component
   ───────────────────────────────────────────────────────────────────────────── */

const inputVariants = cva(
  "flex w-full rounded-lg border bg-transparent px-3 py-2 text-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-foreground-tertiary focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-border-default hover:border-border-strong focus:border-primary focus:ring-2 focus:ring-primary/20",
        error:
          "border-critical-400 focus:border-critical-400 focus:ring-2 focus:ring-critical-400/20",
        success:
          "border-success-500 focus:border-success-500 focus:ring-2 focus:ring-success-500/20",
      },
      size: {
        sm: "h-8 text-xs",
        md: "h-10",
        lg: "h-12 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  },
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {
  error?: boolean;
  success?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  // variant is reserved for future input styling variants

  ({ className, variant: _variant, size, error, success, ...props }, ref) => {
    const { id, error: fieldError, required, disabled } = useFormField();
    const hasError = error || !!fieldError;
    const hasSuccess = success && !hasError;

    return (
      <input
        ref={ref}
        id={id}
        className={cn(
          inputVariants({
            variant: hasError ? "error" : hasSuccess ? "success" : "default",
            size,
          }),
          className,
        )}
        aria-invalid={hasError}
        aria-required={required}
        aria-describedby={hasError ? `${id}-error` : props["aria-describedby"]}
        disabled={disabled || props.disabled}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

/* ─────────────────────────────────────────────────────────────────────────────
   Password Input Component
   ───────────────────────────────────────────────────────────────────────────── */

const PasswordInput = React.forwardRef<
  HTMLInputElement,
  Omit<InputProps, "type">
>(({ className, ...props }, ref) => {
  const [showPassword, setShowPassword] = React.useState(false);

  return (
    <div className="relative">
      <Input
        ref={ref}
        type={showPassword ? "text" : "password"}
        className={cn("pr-10", className)}
        {...props}
      />
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-tertiary hover:text-foreground transition-colors"
        tabIndex={-1}
        aria-label={showPassword ? "Hide password" : "Show password"}
      >
        {showPassword ? (
          <EyeOff className="h-4 w-4" />
        ) : (
          <Eye className="h-4 w-4" />
        )}
      </button>
    </div>
  );
});
PasswordInput.displayName = "PasswordInput";

/* ─────────────────────────────────────────────────────────────────────────────
   Textarea Component
   ───────────────────────────────────────────────────────────────────────────── */

const textareaVariants = cva(
  "flex w-full rounded-lg border bg-transparent px-3 py-2 text-sm transition-colors placeholder:text-foreground-tertiary focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 resize-none",
  {
    variants: {
      variant: {
        default:
          "border-border-default hover:border-border-strong focus:border-primary focus:ring-2 focus:ring-primary/20",
        error:
          "border-critical-400 focus:border-critical-400 focus:ring-2 focus:ring-critical-400/20",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {
  error?: boolean;
  maxLength?: number;
  showCount?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  // variant is reserved for future textarea styling variants

  (
    { className, variant: _variant, error, maxLength, showCount, ...props },
    ref,
  ) => {
    const { id, error: fieldError, disabled } = useFormField();
    const hasError = error || !!fieldError;
    const [value, setValue] = React.useState(
      props.defaultValue || props.value || "",
    );

    const currentLength = String(value).length;
    const isOverLimit = maxLength ? currentLength > maxLength : false;

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setValue(e.target.value);
      props.onChange?.(e);
    };

    return (
      <div className="space-y-1.5">
        <textarea
          ref={ref}
          id={id}
          className={cn(
            textareaVariants({
              variant: hasError || isOverLimit ? "error" : "default",
            }),
            className,
          )}
          aria-invalid={hasError || isOverLimit}
          aria-describedby={showCount ? `${id}-count` : undefined}
          disabled={disabled || props.disabled}
          maxLength={maxLength}
          {...props}
          onChange={handleChange}
        />
        {showCount && (
          <p
            id={`${id}-count`}
            className={cn(
              "text-xs text-right",
              isOverLimit ? "text-critical-400" : "text-foreground-tertiary",
            )}
          >
            {currentLength}
            {maxLength && ` / ${maxLength}`}
          </p>
        )}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";

/* ─────────────────────────────────────────────────────────────────────────────
   Select Component
   ───────────────────────────────────────────────────────────────────────────── */

const selectVariants = cva(
  "flex w-full appearance-none rounded-lg border bg-transparent px-3 py-2 text-sm transition-colors focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-border-default hover:border-border-strong focus:border-primary focus:ring-2 focus:ring-primary/20",
        error:
          "border-critical-400 focus:border-critical-400 focus:ring-2 focus:ring-critical-400/20",
      },
      selectSize: {
        sm: "h-8 text-xs",
        md: "h-10",
        lg: "h-12 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      selectSize: "md",
    },
  },
);

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement>,
    VariantProps<typeof selectVariants> {
  error?: boolean;
  placeholder?: string;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      className,
      variant,
      selectSize,
      size,
      error,
      children,
      placeholder,
      ...props
    },
    ref,
  ) => {
    const { id, error: fieldError, required, disabled } = useFormField();
    const hasError = error || !!fieldError;
    // variant is reserved for future select styling variants
    void variant;
    // Use selectSize prop, fallback to mapping size number to selectSize
    const sizeVariant =
      selectSize || (size === 0 ? "sm" : size && size > 3 ? "lg" : "md");

    return (
      <div className="relative">
        <select
          ref={ref}
          id={id}
          className={cn(
            selectVariants({
              variant: hasError ? "error" : "default",
              selectSize: sizeVariant,
            }),
            "pr-10",
            className,
          )}
          aria-invalid={hasError}
          aria-required={required}
          disabled={disabled || props.disabled}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children}
        </select>
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg
            className="h-4 w-4 text-foreground-tertiary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>
    );
  },
);
Select.displayName = "Select";

/* ─────────────────────────────────────────────────────────────────────────────
   Checkbox Component
   ───────────────────────────────────────────────────────────────────────────── */

const checkboxVariants = cva(
  "peer h-4 w-4 shrink-0 rounded border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: [
          "border-border-strong",
          "data-[state=checked]:bg-primary data-[state=checked]:border-primary",
          "data-[state=indeterminate]:bg-primary data-[state=indeterminate]:border-primary",
        ],
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "size">,
    VariantProps<typeof checkboxVariants> {}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, variant, ...props }, ref) => {
    const { id, disabled } = useFormField();

    return (
      <div className="flex items-start gap-2">
        <input
          ref={ref}
          id={id}
          type="checkbox"
          className={cn(checkboxVariants({ variant }), className)}
          disabled={disabled || props.disabled}
          {...props}
        />
      </div>
    );
  },
);
Checkbox.displayName = "Checkbox";

/* ─────────────────────────────────────────────────────────────────────────────
   Checkbox With Label Component
   ───────────────────────────────────────────────────────────────────────────── */

interface CheckboxWithLabelProps extends CheckboxProps {
  label: React.ReactNode;
  description?: string;
}

const CheckboxWithLabel = React.forwardRef<
  HTMLInputElement,
  CheckboxWithLabelProps
>(({ label, description, className, ...props }, ref) => {
  const { id } = useFormField();

  return (
    <div className={cn("flex items-start gap-3", className)}>
      <Checkbox ref={ref} {...props} />
      <div className="space-y-1 leading-none">
        <label
          htmlFor={id}
          className="text-sm font-medium text-foreground cursor-pointer"
        >
          {label}
        </label>
        {description && (
          <p className="text-xs text-foreground-secondary">{description}</p>
        )}
      </div>
    </div>
  );
});
CheckboxWithLabel.displayName = "CheckboxWithLabel";

/* ─────────────────────────────────────────────────────────────────────────────
   Switch Component
   ───────────────────────────────────────────────────────────────────────────── */

const switchVariants = cva(
  "peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "data-[state=checked]:bg-primary data-[state=unchecked]:bg-bg-floating",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface SwitchProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "size">,
    VariantProps<typeof switchVariants> {}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  // className is reserved for future switch styling
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  ({ className, variant, ...props }, ref) => {
    const { id, disabled } = useFormField();

    return (
      <input
        ref={ref}
        id={id}
        type="checkbox"
        role="switch"
        className={cn("sr-only peer", switchVariants({ variant }))}
        disabled={disabled || props.disabled}
        {...props}
      />
    );
  },
);
Switch.displayName = "Switch";

/* ─────────────────────────────────────────────────────────────────────────────
   Switch With Label Component
   ───────────────────────────────────────────────────────────────────────────── */

interface SwitchWithLabelProps extends SwitchProps {
  label: React.ReactNode;
  description?: string;
}

const SwitchWithLabel = React.forwardRef<
  HTMLInputElement,
  SwitchWithLabelProps
>(({ label, description, className, ...props }, ref) => {
  const { id } = useFormField();

  return (
    <div className={cn("flex items-center justify-between", className)}>
      <div className="space-y-1">
        <label
          htmlFor={id}
          className="text-sm font-medium text-foreground cursor-pointer"
        >
          {label}
        </label>
        {description && (
          <p className="text-xs text-foreground-secondary">{description}</p>
        )}
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <Switch ref={ref} {...props} />
        <span className="ml-3 w-9 h-5 bg-bg-floating peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary" />
      </label>
    </div>
  );
});
SwitchWithLabel.displayName = "SwitchWithLabel";

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export {
  FormField,
  FormLabel,
  FormDescription,
  FormError,
  Input,
  PasswordInput,
  Textarea,
  Select,
  Checkbox,
  CheckboxWithLabel,
  Switch,
  SwitchWithLabel,
  inputVariants,
  textareaVariants,
  selectVariants,
};
