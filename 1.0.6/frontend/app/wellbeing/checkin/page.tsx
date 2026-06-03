import { redirect } from "next/navigation";

export default function WellbeingCheckinRedirect() {
  redirect("/diary?tab=checkin");
}
