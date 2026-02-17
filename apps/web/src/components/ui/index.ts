/**
 * Horizon UI Components
 * Centralized exports for all UI primitives
 */

// Export button from button-horizon
export {
  Button,
  IconButton,
  ButtonGroup,
  buttonVariants,
  type ButtonProps,
  type IconButtonProps,
  type ButtonGroupProps,
} from "./button-horizon";

// Export card components
export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  MotionCard,
  cardVariants,
  type CardProps,
  type CardHeaderProps,
  type CardContentProps,
  type CardFooterProps,
} from "./card";

// Export badge components
export {
  Badge,
  StatusBadge,
  RiskBadge,
  CountBadge,
  badgeVariants,
  statusDotVariants,
  type BadgeProps,
} from "./badge-horizon";

// Export form components
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
  type InputProps,
  type TextareaProps,
  type SelectProps,
  type CheckboxProps,
  type SwitchProps,
} from "./form";

// Export data display components
export {
  DataTable,
  type Column,
  type DataTableProps,
  type SortDirection,
} from "./data-table-horizon";

// Export tabs
export {
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  SegmentedControl,
  type TabsProps,
  type TabProps,
  type TabListProps,
  type TabPanelsProps,
  type TabPanelProps,
  type SegmentedControlProps,
} from "./tabs";

// Export feedback components
export {
  Skeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonMetricCard,
  SkeletonTable,
  SkeletonList,
  SkeletonPage,
  type SkeletonProps,
  type SkeletonTextProps,
  type SkeletonAvatarProps,
  type SkeletonCardProps,
  type SkeletonTableProps,
} from "./skeleton";

export {
  EmptyState,
  EmptySearch,
  EmptyData,
  EmptyInbox,
  EmptyError,
  EmptyInline,
  type EmptyStateProps,
} from "./empty-state";

// Note: EmptyStateInline is exported as EmptyInline from empty-state

// Export toast
export {
  ToastProvider,
  useToast,
  useToastHelpers,
  toast,
  setToastCallback,
  type Toast,
  type ToastVariant,
} from "./toast";

// Export modal components
export {
  Modal,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalBody,
  ModalFooter,
  ConfirmModal,
  Drawer,
  type ModalProps,
  type ModalHeaderProps,
  type ModalFooterProps,
  type ConfirmModalProps,
  type DrawerProps,
} from "./modal";

// Re-export progress components for compatibility
export {
  Progress,
  CircularProgress,
  StepProgress,
  type ProgressColor,
  type ProgressProps,
  type CircularProgressProps,
  type StepProgressProps,
} from "./progress";
