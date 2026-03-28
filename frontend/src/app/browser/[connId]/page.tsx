"use client";

import { use } from "react";
import { redirect } from "next/navigation";

export default function BrowserRedirectPage({ params }: { params: Promise<{ connId: string }> }) {
  const { connId } = use(params);
  redirect(`/cluster/${connId}`);
}
