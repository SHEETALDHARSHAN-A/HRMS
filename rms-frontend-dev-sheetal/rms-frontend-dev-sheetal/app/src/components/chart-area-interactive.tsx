import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type RangeKey = '30d' | '90d' | '180d';

const seriesByRange: Record<RangeKey, number[]> = {
  '30d': [32, 36, 34, 42, 44, 48, 45, 52, 54, 58],
  '90d': [22, 25, 27, 30, 33, 37, 42, 46, 49, 53],
  '180d': [15, 18, 22, 25, 27, 31, 35, 38, 42, 47],
};

const labelsByRange: Record<RangeKey, string[]> = {
  '30d': ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10'],
  '90d': ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10'],
  '180d': ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10'],
};

export function ChartAreaInteractive() {
  const [range, setRange] = useState<RangeKey>('90d');

  const chartPoints = useMemo(() => {
    const values = seriesByRange[range];
    const max = Math.max(...values);
    const min = Math.min(...values);
    const spread = Math.max(1, max - min);

    return values.map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = 100 - ((value - min) / spread) * 80 - 10;
      return `${x},${y}`;
    });
  }, [range]);

  const polylinePoints = chartPoints.join(' ');
  const areaPoints = `0,100 ${polylinePoints} 100,100`;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <CardTitle>Hiring Momentum</CardTitle>
          <CardDescription>
            Applications progressing from screening to final decision.
          </CardDescription>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline">Updated today</Badge>
          {(['30d', '90d', '180d'] as RangeKey[]).map((key) => (
            <Button
              key={key}
              size="sm"
              variant={range === key ? 'default' : 'outline'}
              onClick={() => setRange(key)}
            >
              {key.toUpperCase()}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        <div className="rounded-lg border bg-background p-4">
          <svg viewBox="0 0 100 100" className="h-64 w-full" preserveAspectRatio="none">
            <defs>
              <linearGradient id="hiringTrend" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.35" />
                <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.05" />
              </linearGradient>
            </defs>

            <line x1="0" y1="20" x2="100" y2="20" stroke="hsl(var(--border))" strokeDasharray="2 2" />
            <line x1="0" y1="50" x2="100" y2="50" stroke="hsl(var(--border))" strokeDasharray="2 2" />
            <line x1="0" y1="80" x2="100" y2="80" stroke="hsl(var(--border))" strokeDasharray="2 2" />

            <polygon points={areaPoints} fill="url(#hiringTrend)" />
            <polyline
              points={polylinePoints}
              fill="none"
              stroke="hsl(var(--primary))"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          <div className="mt-3 grid grid-cols-5 gap-2 text-xs text-muted-foreground sm:grid-cols-10">
            {labelsByRange[range].map((label) => (
              <span key={label} className="truncate text-center">
                {label}
              </span>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
