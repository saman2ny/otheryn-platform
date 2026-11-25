import DocsLayout from '../../components/documentation/DocsLayout';

export default function DocumentationPage({ slug }: { slug?: string }) {
  return <DocsLayout slug={slug} />;
}
