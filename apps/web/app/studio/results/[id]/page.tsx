import { ResultsClient } from "./ResultsClient";

export default async function ResultsPage(props: PageProps<"/studio/results/[id]">) {
  const { id } = await props.params;
  return <ResultsClient id={id} />;
}
