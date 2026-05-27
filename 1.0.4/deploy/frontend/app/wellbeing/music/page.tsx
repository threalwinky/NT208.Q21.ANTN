import { redirect } from "next/navigation";

export default function WellbeingMusicRedirect() {
  redirect("/diary?tab=music");
}
