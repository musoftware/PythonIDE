import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello from NestStore - a NestJS app made with RAD IDE!';
  }
}
