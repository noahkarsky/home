from django.urls import path

from . import views


urlpatterns = [

    path( '',
          views.Floorplan3dView.as_view(),
          name = 'floorplan3d_home' ),

    path( 'designer',
          views.Floorplan3dDesignerView.as_view(),
          name = 'floorplan3d_designer' ),

    path( 'backyard',
          views.BackyardView.as_view(),
          name = 'floorplan3d_backyard' ),

    path( 'backyard/app',
          views.BackyardAppView.as_view(),
          name = 'floorplan3d_backyard_app' ),

    path( 'speed',
          views.SpeedTestView.as_view(),
          name = 'floorplan3d_speed' ),

    path( 'apply',
          views.Floorplan3dApplyView.as_view(),
          name = 'floorplan3d_apply' ),
]
