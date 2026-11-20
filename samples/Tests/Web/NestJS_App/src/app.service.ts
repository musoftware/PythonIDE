import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello from NestApp1 - a NestJS app made with RAD IDE!';
  }
}
