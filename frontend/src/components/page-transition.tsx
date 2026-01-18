"use client";

import { motion } from "framer-motion";

export function PageTransition({ children }: { children: React.ReactNode }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ ease: "easeInOut", duration: 0.3 }}
            className="w-full h-full"
        >
            {children}
        </motion.div>
    );
}
