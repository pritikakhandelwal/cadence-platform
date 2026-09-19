import { PickClient } from "./PickClient";

export default async function PickPage(props: PageProps<"/studio/pick/[id]">) {
  const { id } = await props.params;
  return <PickClient id={id} />;
}
