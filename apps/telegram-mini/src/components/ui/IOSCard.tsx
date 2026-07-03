import React from "react";

interface IOSCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  id?: string;
  className?: string;
  glowColor?: string; // e.g. "rgba(124,58,237,0.15)"
  onClick?: () => void;
}

export function IOSCard({ 
  children, 
  id, 
  className = "", 
  glowColor, 
  onClick, 
  ...props 
}: IOSCardProps) {
  const isClickable = !!onClick;

  return (
    <div
      id={id}
      onClick={onClick}
      style={{
        boxShadow: glowColor ? `0 8px 30px ${glowColor}` : undefined,
      }}
      className={`relative rounded-[24px] bg-white/[0.04] border border-white/[0.08] p-4 backdrop-blur-md overflow-hidden transition-all duration-300 ${
        isClickable 
          ? "active:scale-[0.97] hover:bg-white/[0.07] cursor-pointer" 
          : ""
      } ${className}`}
      {...props}
    >
      {/* Subtle overlay reflection */}
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/[0.01] to-white/[0.03] pointer-events-none" />
      {children}
    </div>
  );
}
