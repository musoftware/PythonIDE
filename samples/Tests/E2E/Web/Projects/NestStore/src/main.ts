import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { join } from 'path';
import { randomBytes } from 'crypto';
import { AppModule } from './app.module';

// in-memory sessions (cookie "sid") with a CSRF token
const sessions = new Map<string, Record<string, string>>();

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  app.use((req: any, res: any, next: () => void) => {
    const m = /(?:^|;\s*)sid=([a-f0-9]{32})/.exec(req.headers.cookie || '');
    let sid = m && sessions.has(m[1]) ? m[1] : '';
    if (!sid) {
      sid = randomBytes(16).toString('hex');
      sessions.set(sid, { csrf: randomBytes(16).toString('hex') });
      res.setHeader('Set-Cookie', `sid=${sid}; HttpOnly; SameSite=Lax; Path=/`);
    }
    req.session = sessions.get(sid);
    next();
  });
  app.useStaticAssets(join(process.cwd(), 'public'));
  await app.listen(process.env.PORT ?? 3000, '127.0.0.1');
  console.log(`Application is running on: ${await app.getUrl()}`);
}
bootstrap();
