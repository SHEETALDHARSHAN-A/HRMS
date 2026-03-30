import { Briefcase, CheckCircle2, Clock3, Users } from 'lucide-react';

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { NumberTicker } from '@/components/ui/number-ticker';

const cards = [
  {
    title: 'Open Positions',
    value: 48,
    description: 'Active jobs currently published',
    footer: '+4 this week',
    icon: Briefcase,
  },
  {
    title: 'Applicants',
    value: 1287,
    description: 'Candidates in the pipeline',
    footer: '+12.5% month over month',
    icon: Users,
  },
  {
    title: 'In Review',
    value: 356,
    description: 'Profiles being evaluated',
    footer: '22 urgent profiles',
    icon: Clock3,
  },
  {
    title: 'Hired',
    value: 94,
    description: 'Successful placements this quarter',
    footer: '+8 from previous quarter',
    icon: CheckCircle2,
  },
];

export function SectionCards() {
  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;

        return (
          <Card key={card.title} className="@container/card h-full">
            <CardHeader className="relative pb-2">
              <CardDescription>{card.title}</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                <NumberTicker value={card.value} />
              </CardTitle>
              <span className="absolute top-4 right-4 inline-flex size-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <Icon className="size-4" />
              </span>
            </CardHeader>
            <CardContent className="pt-0 text-xs text-muted-foreground">{card.description}</CardContent>
            <CardFooter className="pt-0 text-xs text-muted-foreground">{card.footer}</CardFooter>
          </Card>
        );
      })}
    </div>
  );
}
