import { ProcessingClient } from "./ProcessingClient";

export default async function ProcessingPage(props: PageProps<"/studio/processing/[id]">) {
  const { id } = await props.params;
  return <ProcessingClient id={id} />;
}
