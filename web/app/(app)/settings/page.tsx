"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Moon, Sun, Monitor, Wifi, WifiOff, Radar, Tag } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useDisplayName } from "@/hooks/use-display-name";
import { useHealth } from "@/hooks/use-health";
import { useAdminSummary } from "@/hooks/use-admin-summary";

const APP_VERSION = "0.1.0";

export default function SettingsPage() {
  const [displayName, setDisplayName] = useDisplayName();
  const { theme, setTheme } = useTheme();
  const { data: health } = useHealth();
  const { data: adminSummary } = useAdminSummary();

  // next-themes can't know the persisted theme during SSR (it lives in localStorage),
  // so `theme` is undefined server-side -- gate theme-dependent styling behind a mounted
  // check to avoid a server/client hydration mismatch on the active-button variant.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const activeTheme = mounted ? theme : undefined;

  const isHealthy = health?.ok && health.data.status === "ok";
  const retrievalBackend = adminSummary?.ok ? adminSummary.data.retrieval_backend : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="mx-auto max-w-2xl space-y-6 p-6"
    >
      <div>
        <h2 className="text-h2 text-foreground">Settings</h2>
        <p className="mt-1 text-body text-muted-foreground">
          Preferences for this browser. There are no user accounts in Nexus today -- every
          request is authenticated with a single shared API key on the server.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Display name</CardTitle>
          <CardDescription>
            Labels your queries in server-side logs. Not a login or identity -- anyone can set
            any value here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Label htmlFor="display-name" className="sr-only">
            Display name
          </Label>
          <Input
            id="display-name"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            className="max-w-xs"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Choose how Nexus looks on this device.</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button
            variant={activeTheme === "light" ? "secondary" : "outline"}
            size="sm"
            className="gap-2"
            onClick={() => setTheme("light")}
          >
            <Sun className="size-4" />
            Light
          </Button>
          <Button
            variant={activeTheme === "dark" ? "secondary" : "outline"}
            size="sm"
            className="gap-2"
            onClick={() => setTheme("dark")}
          >
            <Moon className="size-4" />
            Dark
          </Button>
          <Button
            variant={activeTheme === "system" ? "secondary" : "outline"}
            size="sm"
            className="gap-2"
            onClick={() => setTheme("system")}
          >
            <Monitor className="size-4" />
            System
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>System</CardTitle>
          <CardDescription>Read-only status of the connected Nexus backend.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-body">
            <span className="flex items-center gap-2 text-muted-foreground">
              {isHealthy ? (
                <Wifi className="size-4 text-success" />
              ) : (
                <WifiOff className="size-4 text-destructive" />
              )}
              API connectivity
            </span>
            <span className="font-mono text-body-s">
              {isHealthy ? "Connected" : "Unreachable"}
            </span>
          </div>
          <Separator />
          <div className="flex items-center justify-between text-body">
            <span className="flex items-center gap-2 text-muted-foreground">
              <Radar className="size-4" />
              Retrieval backend
            </span>
            <span className="font-mono text-body-s">{retrievalBackend ?? "unknown"}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between text-body">
            <span className="flex items-center gap-2 text-muted-foreground">
              <Tag className="size-4" />
              Version
            </span>
            <span className="font-mono text-body-s">{APP_VERSION}</span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
