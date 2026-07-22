"use client";

import { useState } from "react";
import { SlidersHorizontal, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { ALLOWED_FILTER_KEYS, type FilterKey } from "@/lib/types";

const FILTER_LABELS: Record<FilterKey, string> = {
  category: "Category",
  department: "Department",
  source_type: "Source type",
  access_level: "Access level",
  tags: "Tags",
};

export type FilterValues = Partial<Record<FilterKey, string>>;

interface FilterBarProps {
  values: FilterValues;
  onChange: (values: FilterValues) => void;
}

export function FilterBar({ values, onChange }: FilterBarProps) {
  const [open, setOpen] = useState(false);
  const activeCount = Object.values(values).filter(Boolean).length;

  function setField(key: FilterKey, value: string) {
    onChange({ ...values, [key]: value });
  }

  function clearAll() {
    onChange({});
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant="outline" size="sm" className="gap-2" />}>
        <SlidersHorizontal className="size-3.5" />
        Filters
        {activeCount > 0 ? (
          <Badge variant="secondary" className="ml-1">
            {activeCount}
          </Badge>
        ) : null}
      </PopoverTrigger>
      <PopoverContent className="w-72 space-y-3" align="start">
        <div className="flex items-center justify-between">
          <span className="text-body-s font-medium text-foreground">Filter results</span>
          {activeCount > 0 ? (
            <Button variant="ghost" size="icon-xs" onClick={clearAll} aria-label="Clear filters">
              <X className="size-3.5" />
            </Button>
          ) : null}
        </div>
        {ALLOWED_FILTER_KEYS.map((key) => (
          <div key={key} className="space-y-1">
            <Label htmlFor={`filter-${key}`} className="text-body-s text-muted-foreground">
              {FILTER_LABELS[key]}
            </Label>
            <Input
              id={`filter-${key}`}
              value={values[key] ?? ""}
              onChange={(event) => setField(key, event.target.value)}
              placeholder={`e.g. ${key === "tags" ? "vpn" : "..."}`}
              className="h-8 text-body-s"
            />
          </div>
        ))}
      </PopoverContent>
    </Popover>
  );
}
