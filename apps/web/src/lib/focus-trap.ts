/**
 * Focus Trap Utility
 * Ensures keyboard navigation stays within a modal/dialog
 */

export interface FocusableElement {
  focus(): void;
  tabIndex: number;
  disabled?: boolean;
  hidden?: boolean;
  offsetParent?: Element | null;
}

const FOCUSABLE_SELECTORS = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
  "details > summary",
  "[contenteditable]",
].join(", ");

export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const elements = Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS),
  );

  // Filter out hidden elements
  return elements.filter((el) => {
    if (el.hasAttribute("disabled")) return false;
    if (el.getAttribute("aria-hidden") === "true") return false;
    if (el.offsetParent === null) return false;

    // Check visibility
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;

    return true;
  });
}

export function trapFocus(
  container: HTMLElement,
  options: {
    initialFocus?: HTMLElement | null;
    returnFocus?: boolean;
  } = {},
) {
  const { initialFocus, returnFocus = true } = options;

  const previouslyFocused = document.activeElement as HTMLElement | null;
  const focusableElements = getFocusableElements(container);

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  // Set initial focus
  if (initialFocus) {
    initialFocus.focus();
  } else if (firstElement) {
    firstElement.focus();
  }

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "Tab") return;

    const activeElement = document.activeElement;

    // If shift + tab on first element, go to last
    if (event.shiftKey) {
      if (
        activeElement === firstElement ||
        !container.contains(activeElement)
      ) {
        event.preventDefault();
        lastElement?.focus();
      }
    } else {
      // If tab on last element, go to first
      if (activeElement === lastElement) {
        event.preventDefault();
        firstElement?.focus();
      }
    }
  };

  const handleFocus = (event: FocusEvent) => {
    const target = event.target as HTMLElement;
    if (!container.contains(target)) {
      event.preventDefault();
      firstElement?.focus();
    }
  };

  document.addEventListener("keydown", handleKeyDown);
  document.addEventListener("focusin", handleFocus, true);

  return () => {
    document.removeEventListener("keydown", handleKeyDown);
    document.removeEventListener("focusin", handleFocus, true);

    if (returnFocus && previouslyFocused) {
      previouslyFocused.focus();
    }
  };
}

export function focusFirstElement(container: HTMLElement) {
  const focusableElements = getFocusableElements(container);
  if (focusableElements.length > 0) {
    focusableElements[0].focus();
  }
}

export function focusLastElement(container: HTMLElement) {
  const focusableElements = getFocusableElements(container);
  if (focusableElements.length > 0) {
    focusableElements[focusableElements.length - 1].focus();
  }
}
