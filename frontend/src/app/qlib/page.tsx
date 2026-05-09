import { redirect } from "next/navigation";

/** Entry point from sidebar; full UI lives under Research Evidence (Qlib tab). */
export default function QlibPage() {
  redirect("/research-evidence?tab=qlib");
}
