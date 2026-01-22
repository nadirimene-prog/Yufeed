import { useEffect, useState } from 'react';
import { HelpCircle, X, Search, Command } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KeyboardShortcut {
    key: string;
    description: string;
    action?: () => void;
}

const shortcuts: KeyboardShortcut[] = [
    { key: '/', description: 'Focus search' },
    { key: 'g d', description: 'Go to Dashboard' },
    { key: 'g a', description: 'Go to Alerts' },
    { key: 'g c', description: 'Go to Cases' },
    { key: 'g n', description: 'Go to Network Analysis' },
    { key: '?', description: 'Show keyboard shortcuts' },
    { key: 'Esc', description: 'Close dialogs' },
];

export function KeyboardShortcutsHelp() {
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        const handleKeyPress = (e: KeyboardEvent) => {
            // Show help with ?
            if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
                const target = e.target as HTMLElement;
                if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    setIsOpen(true);
                }
            }

            // Close with Escape
            if (e.key === 'Escape' && isOpen) {
                setIsOpen(false);
            }
        };

        window.addEventListener('keydown', handleKeyPress);
        return () => window.removeEventListener('keydown', handleKeyPress);
    }, [isOpen]);

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-4 right-4 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all z-50"
                title="Keyboard Shortcuts (Press ?)"
            >
                <HelpCircle className="h-5 w-5" />
            </button>
        );
    }

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-50 animate-fade-in"
                onClick={() => setIsOpen(false)}
            />

            {/* Modal */}
            <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
                <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-700 shadow-2xl max-w-lg w-full animate-slide-up">
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-700">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <Command className="h-5 w-5" />
                            Keyboard Shortcuts
                        </h2>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                        >
                            <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6">
                        <div className="space-y-3">
                            {shortcuts.map((shortcut, index) => (
                                <div
                                    key={index}
                                    className="flex items-center justify-between py-2"
                                >
                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                        {shortcut.description}
                                    </span>
                                    <kbd className="px-3 py-1.5 text-sm font-mono bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded text-gray-900 dark:text-white">
                                        {shortcut.key}
                                    </kbd>
                                </div>
                            ))}
                        </div>

                        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700">
                            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                                Press <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded">Esc</kbd> to close
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
