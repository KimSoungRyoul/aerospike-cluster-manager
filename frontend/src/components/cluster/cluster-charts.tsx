"use client";

import { Database, HardDrive } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltipContent } from "@/components/common/chart-tooltip";
import type { MetricSeries } from "@/lib/api/types";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface ClusterChartsProps {
  tpsData: Array<{ time: string; reads: number; writes: number }>;
  connData: Array<{ time: string; connections: number }>;
  memData: Array<Record<string, string | number>>;
  devData: Array<Record<string, string | number>>;
  memoryUsageByNs: MetricSeries[];
  deviceUsageByNs: MetricSeries[];
}

export function ClusterCharts({
  tpsData,
  connData,
  memData,
  devData,
  memoryUsageByNs,
  deviceUsageByNs,
}: ClusterChartsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Read / Write TPS</CardTitle>
          <CardDescription>Transactions per second over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[180px] sm:h-[220px] lg:h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={tpsData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-base-300" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" width={45} />
                <RechartsTooltip content={<ChartTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                <Line
                  type="monotone"
                  dataKey="reads"
                  stroke="var(--color-chart-1)"
                  strokeWidth={2}
                  dot={false}
                  name="Reads"
                />
                <Line
                  type="monotone"
                  dataKey="writes"
                  stroke="var(--color-chart-2)"
                  strokeWidth={2}
                  dot={false}
                  name="Writes"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Client Connections</CardTitle>
          <CardDescription>Active connections over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[180px] sm:h-[220px] lg:h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={connData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-base-300" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" width={45} />
                <RechartsTooltip content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="connections"
                  stroke="var(--color-chart-3)"
                  strokeWidth={2}
                  dot={false}
                  name="Connections"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Database className="h-4 w-4" />
            Memory Usage by Namespace
          </CardTitle>
          <CardDescription>Percentage of memory used per namespace</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[180px] sm:h-[220px] lg:h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={memData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-base-300" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  width={45}
                  domain={[0, "auto"]}
                  unit="%"
                />
                <RechartsTooltip content={<ChartTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                {memoryUsageByNs.map((s) => (
                  <Area
                    key={s.name}
                    type="monotone"
                    dataKey={s.label}
                    stackId="mem"
                    stroke={s.color}
                    fill={s.color}
                    fillOpacity={0.3}
                    strokeWidth={2}
                    name={s.label}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <HardDrive className="h-4 w-4" />
            Device Usage by Namespace
          </CardTitle>
          <CardDescription>Percentage of device storage used per namespace</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[180px] sm:h-[220px] lg:h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={devData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-base-300" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  className="text-muted-foreground"
                  width={45}
                  domain={[0, "auto"]}
                  unit="%"
                />
                <RechartsTooltip content={<ChartTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                {deviceUsageByNs.map((s) => (
                  <Area
                    key={s.name}
                    type="monotone"
                    dataKey={s.label}
                    stackId="dev"
                    stroke={s.color}
                    fill={s.color}
                    fillOpacity={0.3}
                    strokeWidth={2}
                    name={s.label}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
