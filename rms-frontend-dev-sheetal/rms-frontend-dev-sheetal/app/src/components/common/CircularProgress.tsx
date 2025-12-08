// src/components/common/CircularProgress.tsx
import React from 'react';

interface CircularProgressProps {
  percentage: number;
  size?: number;
  strokeWidth?: number;
}

const CircularProgress: React.FC<CircularProgressProps> = ({
  percentage,
  size = 40,
  strokeWidth = 4,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="transform -rotate-90"
    >
      {/* Background Circle */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        strokeWidth={strokeWidth}
        className="text-gray-200"
        fill="transparent"
        stroke="currentColor"
      />
      {/* Progress Circle */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        strokeWidth={strokeWidth}
        className="text-[var(--color-primary-500)]"
        fill="transparent"
        stroke="currentColor"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.3s ease' }}
      />
      {/* Percentage Text */}
      <text
        x="50%"
        y="50%"
        dy=".3em" // Vertical alignment
        textAnchor="middle" // Horizontal alignment
        className="transform rotate-90"
        style={{
          fontSize: `${size / 3.5}px`, // Dynamic font size
          fill: 'var(--color-primary-500)',
          fontWeight: '600',
        }}
      >
        {`${Math.round(percentage)}%`}
      </text>
    </svg>
  );
};

export default CircularProgress;