export interface EmptyStateConfig {
  image: string | null
  headlines: string[]
  headlineIntervalMs: number
  subtitle: string
  subtitleVisible: boolean
}

export const EMPTY_STATE: EmptyStateConfig = {
  image: null,
  // headlines: [
  //   "What do you want to build?",
  //   "What should we research today?",
  //   "What's broken?",
  //   "What's next on the list?",
  //   "Let's get to work.",
  // ],
  headlines: [
    "Time to cook!",
    "Bugs? No problem!",
    "What's the game plan?",
    "Enter the building room.",
    "Start orchestrating.",
    "What do you want to brainstorm?",
    "From an idea to a product.",
  ],
  headlineIntervalMs: 3500,
  subtitle: "aede, your building room",
  subtitleVisible: true,
}
