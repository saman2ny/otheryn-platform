import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { LoadingBar } from './shared/ui/loading-bar/loading-bar';
import { ToastContainer } from './shared/ui/toast-container/toast-container';

@Component({
  selector: 'dp-root',
  imports: [RouterOutlet, LoadingBar, ToastContainer],
  templateUrl: './app.html',
})
export class App {}
