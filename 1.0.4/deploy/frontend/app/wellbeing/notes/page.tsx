import { redirect } from "next/navigation";

export default function WellbeingNotesRedirect() {
  redirect("/diary?tab=notes");
}
