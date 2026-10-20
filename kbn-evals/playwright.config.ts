import Path from 'path';
import { createPlaywrightEvalsConfig } from '@kbn/evals';

// One Playwright project per connector: the same spec runs against every --model you pass.
export default createPlaywrightEvalsConfig({
  testDir: Path.resolve(__dirname, './evals'),
});
